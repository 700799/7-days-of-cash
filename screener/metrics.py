from typing import Optional, Dict, Any

import numpy as np
import pandas as pd


def compute_metrics(ticker: str, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    try:
        df = df.sort_index()
        close = df["Close"]
        volume = df["Volume"]
        high = df["High"]
        low = df["Low"]

        if len(close) < 10:
            return None

        price = float(close.iloc[-1])

        # 7-day % change (7 trading days back)
        lookback = min(7, len(close) - 1)
        change_7d = (close.iloc[-1] / close.iloc[-1 - lookback] - 1) * 100

        # 20-day average volume
        avg_vol_20d = float(volume.iloc[-20:].mean()) if len(volume) >= 20 else float(volume.mean())

        # Relative volume: today vs 20d avg
        today_vol = float(volume.iloc[-1])
        rel_vol = today_vol / avg_vol_20d if avg_vol_20d > 0 else 0.0

        # Volume trend slopes (linear regression on last N days)
        vol_trend_5d = _linreg_slope(volume.iloc[-5:].values) if len(volume) >= 5 else 0.0
        vol_trend_7d = _linreg_slope(volume.iloc[-7:].values) if len(volume) >= 7 else 0.0

        # RSI(14)
        rsi = _rsi(close, period=14)

        # Avg intraday volatility for penny-stock filter
        avg_range_pct = float(((high - low) / close).iloc[-10:].mean()) * 100

        return {
            "ticker": ticker,
            "price": round(price, 2),
            "change_7d": round(float(change_7d), 2),
            "avg_vol_20d": int(avg_vol_20d),
            "rel_vol": round(rel_vol, 2),
            "vol_trend_5d": round(vol_trend_5d, 0),
            "vol_trend_7d": round(vol_trend_7d, 0),
            "rsi_14": round(rsi, 1),
            "avg_range_pct": round(avg_range_pct, 1),
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
    # Wilder smoothing
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean().iloc[-1]
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100 - 100 / (1 + rs))
